<?php

namespace App\Model;

class User
{
    public ?int $id = null;
    public string $email;
    public string $firstname;
    public string $lastname;

    public static function create(string $email, string $firstname, string $lastname): self
    {
        $u = new self();
        $u->email = $email;
        $u->firstname = $firstname;
        $u->lastname = $lastname;
        return $u;
    }

    public function validate(): string|bool
    {
        if (trim($this->email) === "") {
            return "E-Mail address must be set";
        }

        if (strlen($this->email) > 40) {
            return "E-Mail address too long";
        }

        if (strlen($this->firstname) > 40) {
            return "Firstname too long";
        }

        if (strlen($this->lastname) > 40) {
            return "Lastname too long";
        }

        return true;
    }

    public function getFullname(): string
    {
        return $this->firstname . " " . $this->lastname;
    }
}
