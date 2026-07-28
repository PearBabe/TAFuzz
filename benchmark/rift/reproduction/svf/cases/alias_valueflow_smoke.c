/*
 * Minimal SVF 3.2 smoke input.
 *
 * MAYALIAS and NOALIAS are names recognised by SVF's built-in
 * PointerAnalysis::validateTests protocol when wpa is run with -alias-check.
 * They are declarations only: the bitcode is analysed, not linked/executed.
 */
extern void MAYALIAS(void *left, void *right);
extern void NOALIAS(void *left, void *right);

static int command_value;
static int unrelated_value;

__attribute__((noinline)) static int *forward_pointer(int *input)
{
    return input;
}

__attribute__((noinline)) static void commit_value(int *destination,
                                                    int value)
{
    *destination = value;
}

int main(void)
{
    int *source = &command_value;
    int *through_call = forward_pointer(source);
    int *other = &unrelated_value;

    MAYALIAS(source, through_call);
    NOALIAS(source, other);

    commit_value(through_call, 41);
    return command_value == 41 ? 0 : 1;
}
