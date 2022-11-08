<?php

namespace App\Service;

use App\Model\User;
use App\Persistence\UserDAO;

class UserLoginService
{
    public function __construct(
        private readonly UserDAO $userDAO,
        private readonly SessionService $sessionService
    ) {
    }

    /**
     * Tries to log in a user.
     * If the credentials match a user in the system the session is updated with the user object which is also returned.
     * If the credentials do not match a user, null will be returned
     *
     * @param string $email
     * @param string $password
     * @return User|null
     */
    public function login(string $email, string $password): ?User
    {
        $user = $this->userDAO->getByEmailAndPassword($email, $password);
        if ($user === null) {
            return null;
        }
        $this->sessionService->setUser($user);
        return $user;
    }
}
