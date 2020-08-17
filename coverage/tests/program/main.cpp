int foo()
{
    return 0;
}

int bar()
{
    return 1;
}

int main(int argc, char*[])
{
    const int result = argc > 1 ? foo() : bar();
    return result;
}
