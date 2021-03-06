from __future__ import unicode_literals
import sys
import random
import string
import unicodedata

HUMAN_FRIENDLY_CHARS = '234679ABCDEFGHJKLMNPRSTUVWXYZabcdefghijkmnpqrstuvwxyz'

def get_current_class(session, user):
    '''For teachers, returns the class they are teaching. For students,
    returns the class they are registered for. Returns none otherwise.

    '''
    if user.is_staff:
        classes = user.teaches.filter(dismissed=False) & session.classes.all()
    else:
        classes = user.attends.all() & session.classes.all()
    return classes[0] if classes else None

def calculate_progress(user, assignments):
    '''Calculate and returns a list of percentages, indicating the user's
    progress in the corresponding assignment. As a side effect, it
    adds a 'progress' attribute to assignment objects and a
    'completedstep' attribute to step objects.

    '''
    progresses = []
    completed = user.completed.select_related('step')

    for ass in assignments:
        if not ass.active:
            continue
        step_count = 0
        completed_count = 0
        for step in ass.steps.all():
            step_count += 1
            for com in completed:
                if step == com.step:
                    completed_count += 1
                    step.completedstep = com
                    step.given_values = com.answer.split('\x1e')
                    break
        ass.progress = int(100 * completed_count/step_count) if step_count else 0
        progresses.append(ass.progress)

    return progresses

def duplicate_assignment(modeladmin, request, queryset):
    '''Duplicates an assignment including all underlying steps. Can be used as an admin action.'''

    duplicated_assignments = []
    for assignment in queryset:
        steps = assignment.steps.all()
        assignment.pk = None
        assignment.active = False
        assignment.name = (assignment.name + ' (duplicate)').lstrip()
        assignment.number = None
        assignment.save()
        assignment.steps.all().delete() # this deletes the empty step

        for step in steps:
            right_answers = step.right_answers.all()
            wrong_answers = step.wrong_answers.all()
            clarifications = step.clarifications.all()
            step.pk = None
            step.assignment = assignment
            step.save()

            for right_answer in right_answers:
                right_answer.pk = None
                right_answer.save()

            for wrong_answer in wrong_answers:
                wrong_answer.pk = None
                wrong_answer.save()

            for clarification in clarifications:
                clarification.pk = None
                clarification.save()

        duplicated_assignments.append(assignment)
    return duplicated_assignments
duplicate_assignment.short_description = 'Duplicate the selected assignments'

def random_string(length):
    '''Generates a random string of human friendly characters

    '''
    return ''.join(random.choice(HUMAN_FRIENDLY_CHARS) for x in range(length))

def clean(dirty_filename):
    '''Cleans dirty filenames

    '''
    valid_chars = '-_.() %s%s' % (string.ascii_letters, string.digits)

    # Replace accented characters with unaccented ones
    normalized_filename = unicodedata.normalize('NFKD', dirty_filename)

    # Strip out all characters that are not in @valid_chars
    cleaned_filename = ''.join([c for c in normalized_filename if c in valid_chars])

    return cleaned_filename
