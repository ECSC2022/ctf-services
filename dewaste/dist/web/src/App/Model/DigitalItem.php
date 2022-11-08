<?php

namespace App\Model;

use DateTime;
use DateTimeInterface;

class DigitalItem
{
    /**
     * @param int|null $id
     * @param string $name
     * @param string $description
     * @param int $size in bytes
     * @param string $authToken
     * @param DigitalItemStatus $status
     * @param DateTimeInterface|null $createdAt
     */
    public function __construct(
        public ?int $id,
        public string $name,
        public readonly string $description,
        public int $size,
        public string $authToken = "",
        public DigitalItemStatus $status = DigitalItemStatus::UPLOADED,
        public ?DateTimeInterface $createdAt = null
    ) {
        if ($createdAt === null) {
            $this->createdAt = new DateTime();
        }
    }

    public function validate(): string|bool
    {
        if (strlen($this->description) > 2000) {
            return "Description too long";
        }

        return true;
    }
}
