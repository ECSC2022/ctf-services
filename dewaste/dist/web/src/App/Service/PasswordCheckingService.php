<?php

namespace App\Service;

class PasswordCheckingService
{
    private const MIN_LENGTH = 10;

    public function isValid(string $password): bool
    {
        if (strlen($password) <= self::MIN_LENGTH) {
            return false;
        }

        if (preg_match('/[a-z]/', $password) !== 1) {
            return false;
        }

        if (preg_match('/[A-Z]/', $password) !== 1) {
            return false;
        }

        if (preg_match('/[0-9]/', $password) !== 1) {
            return false;
        }

        return true;
    }

    public function getRequirementsText(): string
    {
        $reqs = [
            "Minimum length of " . self::MIN_LENGTH . " characters",
            "At least 1 lowercase letter",
            "At least 1 uppercase letter",
            "At least 1 digit"
        ];
        return implode(", ", $reqs);
    }
}
