#ifndef WORKERMI_H_
#define WORKERMI_H_
#include <string>

/**
 * @class Worker
 * @brief Abstract base class for all worker types. Stores name and ID.
 */
class Worker
{
private:
  std::string fullname; ///< Worker's full name
  long id;              ///< Employee ID
protected:
  /**
   * @brief Displays worker's name and ID.
   */
  virtual void Data() const;

  /**
   * @brief Prompts for worker's name and ID from input.
   */
  virtual void Get();
public:
  /**
   * @brief Default constructor. Initializes name to "no one" and ID to 0.
   */
  Worker() : fullname("no one"), id(0L) {}

  /**
   * @brief Constructs a Worker with given name and ID.
   * @param s Full name
   * @param n Employee ID
   */
  Worker(const std::string& s, long n)
      : fullname(s), id(n) {};

  /**
   * @brief Pure virtual destructor.
   */
  virtual ~Worker() = 0;

  /**
   * @brief Pure virtual method to set worker data.
   */
  virtual void Set() = 0;

  /**
   * @brief Pure virtual method to display worker data.
   */
  virtual void Show() const = 0;
};


/**
 * @class Waiter
 * @brief Represents a waiter, derived from Worker. Adds panache rating.
 */
class Waiter : virtual public Worker
{
private:
  int panache; ///< Panache rating
protected:
  /**
   * @brief Displays waiter's panache rating.
   */
  void Data() const;

  /**
   * @brief Prompts for waiter's panache rating from input.
   */
  void Get();
public:
  /**
   * @brief Default constructor. Initializes panache to 0.
   */
  Waiter() : Worker(), panache(0) {}

  /**
   * @brief Constructs a Waiter with name, ID, and panache rating.
   * @param s Full name
   * @param n Employee ID
   * @param p Panache rating
   */
  Waiter(const std::string & s, long n, int p = 0)
      : Worker(s, n), panache(p) {}

  /**
   * @brief Constructs a Waiter from Worker and panache rating.
   * @param wk Worker object
   * @param p Panache rating
   */
  Waiter(const Worker& wk, int p = 0)
      : Worker(wk), panache(p) {}

  /**
   * @brief Prompts for all waiter data.
   */
  void Set();

  /**
   * @brief Displays all waiter data.
   */
  void Show() const;
};


/**
 * @class Singer
 * @brief Represents a singer, derived from Worker. Adds vocal range.
 */
class Singer : virtual public Worker
{
protected:
  /**
   * @brief Vocal range types.
   */
  enum { other, alto, contralto, soprano,
        bass, baritone, tenor };
  enum { Vtypes = 7 };

  /**
   * @brief Displays singer's vocal range.
   */
  void Data() const;

  /**
   * @brief Prompts for singer's vocal range from input.
   */
  void Get();
private:
  static const char* pv[Vtypes]; ///< Vocal range names
  int voice; ///< Vocal range index
public:
  /**
   * @brief Default constructor. Initializes voice to 'other'.
   */
  Singer() : Worker(), voice(other) {}

  /**
   * @brief Constructs a Singer with name, ID, and vocal range.
   * @param s Full name
   * @param n Employee ID
   * @param v Vocal range index
   */
  Singer(const std::string& s, long n, int v = other)
      : Worker(s, n), voice(v) {}

  /**
   * @brief Constructs a Singer from Worker and vocal range.
   * @param wk Worker object
   * @param v Vocal range index
   */
  Singer(const Worker & wk, int v = other)
      : Worker(wk), voice(v) {}

  /**
   * @brief Prompts for all singer data.
   */
  void Set();

  /**
   * @brief Displays all singer data.
   */
  void Show() const;
};


/**
 * @class SingingWaiter
 * @brief Represents a singing waiter, combining Singer and Waiter roles.
 */
class SingingWaiter : public Singer, public Waiter
{
protected:
  /**
   * @brief Displays both singer and waiter data.
   */
  void Data() const;

  /**
   * @brief Prompts for both singer and waiter data from input.
   */
  void Get();
public:
  /**
   * @brief Default constructor.
   */
  SingingWaiter() {}

  /**
   * @brief Constructs a SingingWaiter with name, ID, panache, and vocal range.
   * @param s Full name
   * @param n Employee ID
   * @param p Panache rating
   * @param v Vocal range index
   */
  SingingWaiter(const std::string& s, long n, int p = 0,
                int v = other)
      : Worker(s, n), Waiter(s, n, p), Singer(s, n, v) {}

  /**
   * @brief Constructs a SingingWaiter from Worker, panache, and vocal range.
   * @param wk Worker object
   * @param p Panache rating
   * @param v Vocal range index
   */
  SingingWaiter(const Worker& wk, int p = 0, int v = other)
      : Worker(wk), Waiter(wk, p), Singer(wk, v) {}

  /**
   * @brief Constructs a SingingWaiter from Waiter and vocal range.
   * @param wt Waiter object
   * @param v Vocal range index
   */
  SingingWaiter(const Waiter& wt, int v = other)
      : Worker(wt), Waiter(wt), Singer(wt, v) {}

  /**
   * @brief Constructs a SingingWaiter from Singer and panache.
   * @param wt Singer object
   * @param p Panache rating
   */
  SingingWaiter(const Singer& wt, int p = 0)
      : Worker(wt), Waiter(wt, p), Singer(wt) {}

  /**
   * @brief Prompts for all singing waiter data.
   */
  void Set();

  /**
   * @brief Displays all singing waiter data.
   */
  void Show() const;
};

#endif