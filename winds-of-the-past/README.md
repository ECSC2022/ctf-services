Winds of the Past
=================
Technology left from the unconcerned past heavily relied on electricity to work. However, in a desperate attempt to stop climate change, most conventional power plants were abandoned and are not functional anymore. While this might have helped to prevent even more dramatic effects on our climate, electricity is now a scarce property.

Wind turbines are one of the primary sources of electrical energy left by previous generations. But to work correctly, they require constant maintenance and a reliable electrical network to distribute and store the energy produced. Unfortunately, recent fights among local communities disrupted previous attempts to improve the existing turbine management system, and we are still stuck with an outdated piece of software.


Overview
--------

The service represents a management platform for wind turbines.

Following actions are available:

* Register user (public)
* Login (public)
* Show details of a single user (internal)
* Register turbine (internal)
* Show details of a single turbine (internal)
* Calculate network capacity (internal)

User properties:

* Username
* Password

Turbine properties:

* ID (generated automatically)
* Description
* Checksum (custom algorithm)
* Model (selection of a set of hardcoded models)

Complete Fortran source code of the application is provided. Users and turbines are automatically deleted by a cronjob if they are not used for a specified amount of time.

Vulnerabilities
---------------

The service has two flag stores.

### Flag Store 1: Logic Flaw

The application contains a logic flaw based on a language-specific feature (implicit `save` attributes). Flags are stored as user password and identified by the corresponding username. Exploiting the logic flaw allows to login as an arbitrary user without knowing the respective password.

Correct initialization of the login status variable prevents this issue.

### Flag Store 2: Missing Authorization Check

Turbines do not have any reference to the registering user. Any user knowing the turbine ID can bruteforce the respective checksum with a maximum of 5 attempts. Flags are stored in the turbine description and identified by the automatically assigned turbine ID.

To fix this issue, add a reference to the registering user to the stored turbines. Check the if the currently logged in user matches the user that registered the turbine before displaying the turbine's details.

### Wildcard Vulnerability: Buffer Overflow

The service calculates some statistical metrics based on a provided squared user consumption matrix (3x3). The local variable `k` is initialized once but later overwritten in the loop. This can be exploited by calling the method that calculates the consumption twice and corrupting the stack. The attacker has to call the calculation twice to trigger the bug and provide an input matrix that leads to an input value being increased to the maximum number of iterations. A user can enter an initial vector used in the power method to approximate the largest eigenvalue of the consumption matrix, and, thus, determine the largest variation. The attacker can in the first step overwrite a function pointer pointing to the `pretty_print` or the return address and has to encode the addresses in the IEE 754 format. If the users only fix the function pointer, the overflow can be exploited with a common ROP chain to one of usages of the `system` function. As users will frequently modify the binary an attacker might has to blindly ROP in a small address search space, which makes the exploitation harder.

Correct initialization of the loop variable prevents this issue. Additionally, unused code (`show_all_turbines`) should be removed to make ROP attacks harder.
