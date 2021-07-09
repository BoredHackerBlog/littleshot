rule username
{
    strings:
        $a = "username"

    condition:
        $a
}
