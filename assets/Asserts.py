
from logging import warning

# Performs an equality assertion with a descriptive failture message that includes the type of data being compared
# and the actual/expected values, like the following example:
#  "Expected signature RIFF, received \x00x\12\x13\xff"
def assert_equal(actual_value, expected_value, displayed_datatype = 'value', warn_not_raise = False):
    # CREATE THE MESSAGE TO DISPLAY IF THE ACTUAL AND EXPECTED VALUES ARE NOT EQUAL.
    # If value(s) to compare are integers, the value(s) will be displayed in hexadecimal.
    # Otherwise, the value(s) will be displayed exactly as they were provided. 
    actual_value_representation = f'0x{actual_value:0>4x}' if isinstance(actual_value, int) else f'{actual_value}'
    expected_value_representation = f'0x{expected_value:0>4x}' if isinstance(expected_value, int) else f'{expected_value}'
    assertion_failure_message = f'Expected {displayed_datatype} {expected_value_representation}, received {actual_value_representation}'

    # PERFORM THE ASSERTION.
    # TODO: Add an exception handler that prints out the current position of the currently-open file (if any).
    try:
        assert actual_value == expected_value, assertion_failure_message
    except AssertionError:
        if warn_not_raise:
            # ISSUE A WARNING.
            # In this instance, execution should continue as normal.
            warning(assertion_failure_message)
        else:
            # RE-RAISE THE ASSERTION ERROR.
            raise
