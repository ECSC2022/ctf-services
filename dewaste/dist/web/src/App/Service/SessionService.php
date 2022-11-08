<?php

namespace App\Service;

use App\Model\User;

class SessionService
{
    private const USER_KEY = "user";

    private function ensureStarted(): void
    {
        if (session_id() === "") {
            session_start();
        }
    }

    public function setUser(?User $user): void
    {
        $this->ensureStarted();
        if ($user !== null) {
            $_SESSION[self::USER_KEY] = $user;
        } else {
            unset($_SESSION[self::USER_KEY]);
        }
    }

    public function getUser(): ?User
    {
        $this->ensureStarted();
        return $_SESSION[self::USER_KEY] ?? null;
    }
}
