<?php

namespace App\Service\Analysis;

use App\Model\Analysis\AnalysisResult;
use App\Model\DigitalItem;
use App\Model\User;

abstract class AnalysisMethod
{
    public function __construct(
        public readonly string $name
    ) {
    }

    /**
     * @param User|null $user
     * @param DigitalItem $item
     * @param string $data
     * @return array<AnalysisResult>
     */
    abstract public function run(?User $user, DigitalItem $item, string $data): array;
}
