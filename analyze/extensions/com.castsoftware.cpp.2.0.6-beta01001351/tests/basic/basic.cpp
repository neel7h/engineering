class AbstractBase
{
public:
    virtual void f() {}
    virtual void g() = 0;
};
 
class Base : public AbstractBase
{
public:
    void f() override  {}
    void g() override  {}
};
 
class Child : public Base
{
public:
    void f() override {}
    void g() override {}
};
 
void g(Base &b)
{
    b.f();
    b.g();
}
 
 
int main()
{
    Base b;
    Child c;
    AbstractBase *ab1 = &b;
    AbstractBase *ab2 = &c;
 
    ab1->f();
    ab1->g();
    ab2->f();
    ab2->g();
 
    g(b);
    g(c);
}
