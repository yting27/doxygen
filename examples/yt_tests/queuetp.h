#pragma once

/**
 * @brief Fixed-capacity FIFO queue implemented with a singly linked list.
 * @tparam T Element type stored in the queue. Must be CopyInsertable into Node::item.
 *
 * @invariant 0 <= items <= qSize
 * @invariant (items == 0) => (front == nullptr && rear == nullptr)
 * @invariant (items > 0)  => (front != nullptr && rear != nullptr)
 *
 * @note Not thread-safe.
 */
template <typename T>
class QueueTp
{
private:
    /// @brief Default capacity used when no size is specified.
    const static int QUEUE_SIZE = 10;

    /**
     * @brief Internal node for the singly linked list.
     * @warning Implementation detail; not part of the public API.
     */
    struct Node
    {
        T item;     ///< Stored value.
        Node *next; ///< Pointer to the next node; nullptr if this is the tail.
    };

    Node *front; ///< Pointer to the first node (head) or nullptr if empty.
    Node *rear;  ///< Pointer to the last node (tail) or nullptr if empty.

    int items;       ///< Current number of elements in the queue.
    const int qSize; ///< Maximum number of elements allowed in the queue.

    /**
     * @brief Copy constructor declared but not defined to prevent copying.
     * @note Intentionally private; using it will cause a link-time error.
     */
    QueueTp(const QueueTp<T> &q) = delete;

    /**
     * @brief Copy assignment declared but not defined to prevent copying.
     * @note Intentionally private; using it will cause a link-time error.
     */
    QueueTp<T> &operator=(const QueueTp<T> &q) = delete;

public:
    /**
     * @brief Constructs an empty queue with a fixed capacity.
     * @param qs Maximum number of elements the queue can hold.
     * @pre qs > 0
     * @post isEmpty() == true && QueueCount() == 0
     */
    QueueTp(int qs = QUEUE_SIZE);

    /**
     * @brief Enqueues (pushes) an element at the back of the queue.
     * @param item The value to append.
     * @return true if the element was enqueued; false if the queue is full.
     * @complexity O(1)
     */
    bool Enqueue(const T &item);

    /**
     * @brief Dequeues (pops) the element at the front of the queue.
     * @param[out] item Receives the removed value if one exists.
     * @return true if an element was dequeued; false if the queue is empty.
     * @complexity O(1)
     */
    bool Dequeue(T &item);

    /**
     * @brief Checks whether the queue contains no elements.
     * @return true if empty; otherwise false.
     */
    bool isEmpty() const { return items == 0; }

    /**
     * @brief Checks whether the queue has reached its capacity.
     * @return true if full; otherwise false.
     */
    bool isFull() const { return items == qSize; }

    /**
     * @brief Returns the current number of elements in the queue.
     * @return Element count in the range [0, qSize].
     */
    int QueueCount() const { return items; }
};