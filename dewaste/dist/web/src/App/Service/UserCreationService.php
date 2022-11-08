<?php

namespace App\Service;

use App\Model\DuplicateEmailAddressException;
use App\Model\User;
use App\Persistence\UserDAO;
use InvalidArgumentException;

class UserCreationService
{
    public function __construct(
        private readonly UserDAO $userDAO,
        private readonly PasswordCheckingService $passwordCheckingService,
        private readonly SessionService $sessionService
    ) {
    }

    /**
     * @param User $user
     * @param string $newPassword
     * @return User
     * @throws InvalidArgumentException in case the password does not follow the guidelines.
     * @throws DuplicateEmailAddressException
     */
    public function create(User $user, string $newPassword): User
    {
        if (!$this->passwordCheckingService->isValid($newPassword)) {
            throw new \InvalidArgumentException(
                "Invalid password. The password needs to follow the following requirements: "
                . $this->passwordCheckingService->getRequirementsText()
            );
        }
        $this->userDAO->create($user, $newPassword);
        $this->sessionService->setUser($user);
        return $user;
    }
}
