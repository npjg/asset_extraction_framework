
from logging import warning

## Performs an equality assertion with a descriptive failture message that includes the type of data being compared
## and the actual/expected values, like the following examples:
##  "Expected <displayed_datatype> <expected_value>, received <received_value>"
##  "Expected signature RIFF, received \x00x\12\x13\xff"
## \param[in] received_value - The value actually observed.
##            In the example above, this is "\x00x\12\x13\xff"
## \param[in] expected_value - The value to which the received value should be compared.
## \param[in] displayed_datatype - The datatype of the received and expected values.
## \param[in] warn_only - When True, do not raise an exception for a failed assertion; rather, print a warning and return False.
def assert_equal(received_value, expected_value, displayed_datatype = 'value', warn_only = False) -> bool:
    # CREATE THE MESSAGE TO DISPLAY IF THE ACTUAL AND EXPECTED VALUES ARE NOT EQUAL.
    # If value(s) to compare are integers, the value(s) will be displayed in hexadecimal.
    # Otherwise, the value(s) will be displayed exactly as they were provided. 
    actual_value_representation = f'0x{received_value:0>4x}' if isinstance(received_value, int) else f'{received_value}'
    expected_value_representation = f'0x{expected_value:0>4x}' if isinstance(expected_value, int) else f'{expected_value}'
    assertion_failure_message = f'Expected {displayed_datatype} {expected_value_representation}, received {actual_value_representation}'

    # PERFORM THE ASSERTION.
    # TODO: Add an exception handler that prints out the current position of the currently-open file (if any).
    try:
        assert received_value == expected_value, assertion_failure_message
    except AssertionError:
        if warn_only:
            # ISSUE A WARNING.
            # In this instance, execution should continue as normal.
            warning(assertion_failure_message)
            # INDICATE THE ASSERTION FAILED.
            return False
        else:
            # RE-RAISE THE ASSERTION ERROR.
            raise

    # INDICATE THE ASSERTION SUCCEEDED.
    return True
