<?php

namespace App\Model;

use DateTime;

class PhysicalItem
{
    /**
     * @param int|null $id
     * @param string $serial
     * @param string $description
     * @param int $length in centimeters
     * @param int $width in centimeters
     * @param int $height in centimeters
     * @param float $weight in kilograms
     * @param string $authToken
     * @param PhysicalItemStatus $status
     */
    public function __construct(
        public ?int $id,
        public readonly string $serial,
        public readonly string $description,
        public readonly int $length,
        public readonly int $width,
        public readonly int $height,
        public readonly float $weight,
        public string $authToken = "",
        public PhysicalItemStatus $status = PhysicalItemStatus::REGISTERED,
        public ?\DateTimeInterface $createdAt = null
    ) {
        if ($createdAt === null) {
            $this->createdAt = new DateTime();
        }
    }

    public function validate(): string|bool
    {
        if (trim($this->serial) === "") {
            return "Serial number empty";
        }

        if (strlen($this->serial) > 64) {
            return "Serial number too long";
        }

        if (strlen($this->description) > 2000) {
            return "Description too long";
        }

        if ($this->length < 0) {
            return "How can your length be negative?";
        }

        if ($this->width < 0) {
            return "How can your width be negative?";
        }

        if ($this->height < 0) {
            return "How can your height be negative?";
        }

        if ($this->weight < 0) {
            return "How can your weight be negative?";
        }

        return true;
    }
}
