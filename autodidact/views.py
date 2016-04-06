import sys
from datetime import datetime, timedelta
from django.http import Http404, HttpResponseForbidden, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.core.urlresolvers import reverse
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.admin.views.decorators import staff_member_required

from .decorators import *
from .utils import *
from .models import *

@login_required
def page(request, slug=''):
    page = get_object_or_404(Page, slug=slug)
    programmes = Programme.objects.all()
    return render(request, 'autodidact/page.html', {
        'page': page,
        'programmes': programmes,
    })

@login_required
@needs_course
def course(request, course):
    return render(request, 'autodidact/course.html', {
        'course': course,
    })

@login_required
@needs_course
@needs_session
def session(request, course, session):
    user = request.user
    current_class = None
    ticket_error = False
    assignments = session.assignments.prefetch_related('steps')
    (answers, progress) = calculate_progress(user, assignments)
    students = None

    if session.registration_enabled:
        if request.method == 'POST':
            ticket = request.POST.get('ticket')
            try:
                newclass = Class.objects.get(ticket=ticket)
            except Class.DoesNotExist:
                newclass = None
            if newclass and newclass.session == session and not newclass.dismissed:
                newclass.students.add(user)
                return redirect(session)
            else:
                ticket_error = ticket

        current_class = get_current_class(session, user)
        if user.is_staff and current_class:
            students = current_class.students.all()
            for s in students:
                (answers, progress) = calculate_progress(s, assignments)
                s.progress = progress
                s.answers = answers

    return render(request, 'autodidact/session_base.html', {
        'course': course,
        'session': session,
        'assignments': assignments,
        'answers': answers,
        'progress': progress,
        'students': students,
        'current_class': current_class,
        'ticket_error': ticket_error,
    })

@staff_member_required
@needs_course
@needs_session
def progress(request, course, session, username):
    try:
        student = get_user_model().objects.get(username=username)
    except get_user_model().DoesNotExist:
        raise Http404
    assignments = session.assignments.prefetch_related('steps')
    (answers, progress) = calculate_progress(student, assignments)
    current_class = get_current_class(session, request.user)
    return render(request, 'autodidact/session_progress.html', {
        'course': course,
        'session': session,
        'assignments': assignments,
        'answers': answers,
        'progress': progress,
        'student': student,
        'current_class': current_class,
    })

@staff_member_required
@needs_course
@needs_session
def progresses(request, course, session):
    try:
        days = int(request.GET['days'])
    except (ValueError, KeyError):
        return HttpResponseBadRequest('Days not specified')
    if days < 0 or days > 365000:
        return HttpResponseBadRequest('Invalid number of days')
    filetype = request.GET.get('filetype')
    assignments = session.assignments.prefetch_related('steps')
    current_class = get_current_class(session, request.user)
    enddate = datetime.today() + timedelta(days=1)
    startdate = enddate - timedelta(days=days+1)
    classes = Class.objects.filter(session=session, date__range=[startdate, enddate]).prefetch_related('students')
    students = get_user_model().objects.filter(attends__in=classes).distinct()
    for s in students:
        (answers, progress) = calculate_progress(s, assignments)
        s.progress = progress
        s.answers = answers

    if filetype == 'csv':
        response = render(request, 'autodidact/students.csv', {'assignments': assignments, 'students': students})
        response['Content-Disposition'] = 'attachment; filename="{}_session{}.csv"'.format(course.slug, session.nr)
        return response
    else:
        return render(request, 'autodidact/session_progresses.html', {
        'days': days,
        'course': course,
        'session': session,
        'assignments': assignments,
        'students': students,
        'current_class': current_class,
    })

@login_required
@needs_course
@needs_session
@needs_assignment
def assignment(request, course, session, assignment):
    steps = list(assignment.steps.all())
    try:
        step_nr = int(request.GET.get('step', 1))
    except ValueError:
        return HttpResponseBadRequest('Invalid step number')
    if step_nr < 1 or step_nr > sys.maxsize:
        return HttpResponseBadRequest('Invalid step number')
    try:
        step = steps[step_nr-1]
        step.nr = step_nr
    except IndexError:
        raise Http404
    try:
        completedstep = request.user.completed.get(step=step)
    except CompletedStep.DoesNotExist:
        completedstep = None

    if request.method == 'POST':
        answer = request.POST.get('answer', '')
        if completedstep:
            completedstep.answer = answer
            completedstep.save()
        else:
            CompletedStep(step=step, whom=request.user, answer=answer).save()
        if 'previous' in request.POST:
            return redirect(reverse('assignment', args=[course.slug, session.nr, assignment.nr]) + "?step=" + str(step_nr - 1))
        elif 'next' in request.POST:
            return redirect(reverse('assignment', args=[course.slug, session.nr, assignment.nr]) + "?step=" + str(step_nr + 1))
        else:
            return redirect(session)

    # Calculate for all steps whether they have answers
    step_overview = []
    all_answers = request.user.completed.filter(step__assignment=assignment).select_related('step')
    answered_steps = [ans.step for ans in all_answers]
    for s in steps:
        if s in answered_steps:
            step_overview.append(True)
        else:
            step_overview.append(False)

    last = step == s
    first = step == steps[0]
    count = len(steps)

    return render(request, 'autodidact/assignment.html', {
        'course': course,
        'session': session,
        'assignment': assignment,
        'step': step,
        'count': count,
        'completedstep': completedstep,
        'step_overview': step_overview,
        'first': first,
        'last': last,
    })

@staff_member_required
@require_http_methods(['POST'])
def startclass(request):
    session_pk = request.POST.get('session')
    class_nr = request.POST.get('class_nr')
    if not class_nr or len(class_nr) > 16:
        return HttpResponseBadRequest()
    session = get_object_or_404(Session, pk=session_pk)

    # Generate unique registration code
    unique = False
    while not unique:
        ticket = random_string(TICKET_LENGTH)
        if not Class.objects.filter(ticket=ticket).exists():
            unique = True

    Class(session=session, number=class_nr, ticket=ticket, teacher=request.user).save()
    return redirect(session)

@staff_member_required
@require_http_methods(['POST'])
def endclass(request):
    class_pk = request.POST.get('class')
    session_pk = request.POST.get('session')
    session = get_object_or_404(Session, pk=session_pk)
    try:
        group = Class.objects.get(pk=class_pk)
        group.teacher = None
        group.dismissed = True
        group.save()
    except Class.DoesNotExist:
        pass
    return redirect(session)

@staff_member_required
@permission_required('autodidact.change_assignment')
@needs_course
@needs_session
def add_assignment(request, course, session):
    assignment = Assignment(session=session)
    assignment.save()
    return HttpResponseRedirect(reverse('admin:autodidact_assignment_change', args=[assignment.pk]))

@staff_member_required
@permission_required('autodidact.change_step')
@needs_course
@needs_session
@needs_assignment
def add_step(request, course, session, assignment):
    step = Step(assignment=assignment)
    step.save()
    return HttpResponseRedirect(reverse('admin:autodidact_step_change', args=[step.pk]))
