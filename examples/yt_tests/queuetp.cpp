#include "queuetp.h"


template <typename T>
QueueTp<T>::QueueTp(int qs)
    : front(nullptr), rear(nullptr), items(0), qSize(qs)
{
}

template <typename T>
QueueTp<T>::~QueueTp()
{
    Node *temp;

    while (front != nullptr)
    {
        temp = front;
        front = front->next;
        delete temp;
    }
}

template <typename T>
bool QueueTp<T>::Enqueue(const T &item)
{
    if (isFull())
        return false;

    Node *add = new Node;
    add->item = item;
    add->next = nullptr;
    items++;

    if (front == nullptr)
        front = add;
    else
        rear->next = add;

    rear = add;

    return true;
}

template <typename T>
bool QueueTp<T>::Dequeue(T &item)
{
    if (front == nullptr)
        return false;

    item = front->item;
    items--;

    Node *temp = front;
    front = front->next;
    delete temp;

    if (items == 0)
        rear = nullptr;

    return true;
}