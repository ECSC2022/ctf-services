# dewaste

## Flag IDs
A short disclaimer about the flag IDs for flagstore 1.

There is additional structure to the flag ids. Depending on the start of the flag id string, the flag is stored differently.

Flag id types (everything before the first '-'):
* physical_acc: `physical_acc-{email}-{item_id}`
* physical_noacc: `physical_noacc-{item_id}`
* digital_acc: `digital_acc-{email}-{item_id}`
* digital_noacc: `digital_noacc-{item_id}`

In this format you find:
* Which type of item you are looking for (physical or digital)
* The id of the item that you are looking for
* In case an account is used to register the item, you have the email address of the registering user account

Flagstore 2 does not have any flag ID associated.

Happy hacking!
