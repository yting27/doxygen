#pragma once
#include "port.h"


/**
 * @class VintagePort
 * @brief Represents a vintage port wine, extending Port with nickname and year.
 */
class VintagePort : public Port
{
private:
  char *nickname; ///< Dynamically allocated nickname for the vintage port
  int year;       ///< Year of the vintage

public:
  /**
   * @brief Default constructor. Initializes as "none" brand, "vintage" style, nickname "none", year 0.
   */
  VintagePort();

  /**
   * @brief Constructs a VintagePort with brand, bottle count, nickname, and year.
   * @param br Brand name (C-string)
   * @param b Number of bottles
   * @param nn Nickname (C-string)
   * @param y Year of vintage
   */
  VintagePort(const char *br, int b, const char *nn, int y);

  /**
   * @brief Copy constructor. Copies all fields from another VintagePort.
   * @param vp VintagePort object to copy from
   */
  VintagePort(const VintagePort &vp);

  /**
   * @brief Destructor. Frees allocated nickname memory.
   */
  ~VintagePort() { delete[] nickname; }

  /**
   * @brief Assignment operator. Copies all fields from another VintagePort.
   * @param vp VintagePort object to assign from
   * @return Reference to this VintagePort
   */
  VintagePort &operator=(const VintagePort &vp);

  /**
   * @brief Displays all information about the vintage port, including nickname and year.
   */
  void Show() const;

  /**
   * @brief Sets the nickname for the vintage port.
   * @param nn Nickname (C-string)
   */
  void SetNN(const char *nn);

  /**
   * @brief Outputs all information about the vintage port to the given output stream.
   * @param os Output stream
   * @param vp VintagePort object to output
   * @return Reference to output stream
   */
  friend std::ostream &operator<<(std::ostream &os, const VintagePort &vp);
};
