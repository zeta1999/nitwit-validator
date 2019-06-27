extern void __VERIFIER_error();
#include <stdio.h>

void blah (void asdf(int, int)) {
    asdf(1, 2);
    return;
}

int func1(char x){
    printf("1: %c\n", x);
    return x;
}

int func2(char y) {
    printf("2: %c\n", y);
    return y;
}

void f(int a, int b){
    printf("blah\n");
    return;
}

double error(char x, int y, short z) {
    __VERIFIER_error();
    return 1.0;
}

int main()
{
    int (*y)(char) = &func2;
    int (*x)(char);

    y('2');
    x = (int (*)(char)) &func1;
    x('1');
    x = &func2;
    x('2');
    (*x)('2');
    x = 0;
    x = &func1;
    x('1');

    int (*arr[3])(char) = {&func1, &func2, &func2};

    arr[0]('1');
    arr[1]('2');
    arr[2]('2');

    blah(f);

    double (*f)(char, int, short) = &error;
    (*f)('s', 1, 2);
    return 0;
}

