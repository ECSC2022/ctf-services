<?php

namespace App\Service;

use App\Model\DigitalItem;
use App\Model\PhysicalItem;
use App\Model\User;
use App\Persistence\DigitalItemDAO;
use AssertionError;

class DigitalItemRegistrationService
{
    public function __construct(private readonly DigitalItemDAO $digitalItemDAO)
    {
    }

    /**
     * @param DigitalItem $item
     * @param string $content
     * @param User|null $user
     * @return void
     */
    public function register(DigitalItem $item, string $content, ?User $user): void
    {
        if ($user === null) {
            $item->authToken = bin2hex(openssl_random_pseudo_bytes(20));
        }

        $this->digitalItemDAO->insert($item, $content);

        if ($item->id === null) {
            throw new AssertionError("Storing the item did not work");
        }

        if ($user !== null) {
            if ($user->id === null) {
                throw new AssertionError("User has to have an id set");
            }
            $this->digitalItemDAO->linkToUser($item->id, $user->id);
            $this->sendThankYouMail($item, $user);
        }
    }

    private function sendThankYouMail(DigitalItem $item, User $user): void
    {
        # TODO implement
    }
}
