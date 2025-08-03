#pragma once
#include <iostream>


/**
 * @class Port
 * @brief Represents a wine port with brand, style, and bottle count.
 */
class Port
{
private:
  char* brand;      ///< Dynamically allocated brand name
  char style[20];   ///< Style of the port
  int bottles;      ///< Number of bottles
public:
  /**
   * @brief Constructs a Port object with given brand, style, and bottle count.
   * @param br Brand name (C-string)
   * @param st Style (C-string, max 19 chars)
   * @param b Number of bottles
   */
  Port(const char* br = "none", const char* st = "none", int b = 0);

  /**
   * @brief Copy constructor. Copies brand, style, and bottle count from another Port.
   * @param p Port object to copy from
   */
  Port(const Port& p);

  /**
   * @brief Destructor. Frees allocated brand memory.
   */
  virtual ~Port() { delete[] brand; }

  /**
   * @brief Assignment operator. Copies brand, style, and bottle count from another Port.
   * @param p Port object to assign from
   * @return Reference to this Port
   */
  Port& operator=(const Port& p);

  /**
   * @brief Adds bottles to the port. If negative, subtracts bottles.
   * @param b Number of bottles to add (can be negative)
   * @return Reference to this Port
   */
  Port& operator+=(int b);

  /**
   * @brief Subtracts bottles from the port. If more than available, prints error.
   * @param b Number of bottles to subtract
   * @return Reference to this Port
   */
  Port& operator-=(int b);

  /**
   * @brief Returns the number of bottles.
   * @return Bottle count
   */
  int BottleCount() const { return bottles; }

  /**
   * @brief Displays port information to standard output.
   */
  virtual void Show() const;

  /**
   * @brief Outputs port information to the given output stream.
   * @param os Output stream
   * @param p Port object to output
   * @return Reference to output stream
   */
  friend std::ostream& operator<<(std::ostream& os, const Port& p);
};
