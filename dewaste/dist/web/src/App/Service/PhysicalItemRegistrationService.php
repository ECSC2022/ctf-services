<?php

namespace App\Service;

use App\Model\PhysicalItem;
use App\Model\User;
use App\Persistence\PhysicalItemDAO;
use AssertionError;

class PhysicalItemRegistrationService
{
    public function __construct(private readonly PhysicalItemDAO $physicalItemDAO)
    {
    }

    /**
     * @param PhysicalItem $item
     * @param User|null $user
     * @return void
     * @throws \App\Model\DuplicateSerialNumberException
     */
    public function register(PhysicalItem $item, ?User $user): void
    {
        if ($user === null) {
            $item->authToken = bin2hex(openssl_random_pseudo_bytes(20));
        }

        $this->physicalItemDAO->insert($item);

        if ($item->id === null) {
            throw new AssertionError("Storing the physical item did not work");
        }

        if ($user !== null) {
            if ($user->id === null) {
                throw new AssertionError("User has not ID set");
            }

            $this->physicalItemDAO->linkToUser($item->id, $user->id);
            $this->sendThankYouMail($item, $user);
        }
    }

    private function sendThankYouMail(PhysicalItem $item, User $user): void
    {
        # TODO implement
    }
}
