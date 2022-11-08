<?php

namespace App\Service;

use App\Model\Analysis\AnalysisResult;
use App\Model\DigitalItem;
use App\Persistence\AnalysisResultDAO;
use App\Persistence\DigitalItemDAO;
use App\Persistence\UserDAO;
use App\Service\Analysis\AnalysisEngine;
use AssertionError;
use Psr\Log\LoggerAwareTrait;

class DigitalItemService
{
    use LoggerAwareTrait;

    public function __construct(
        private readonly DigitalItemDAO $digitalItemDAO,
        private readonly AnalysisEngine $analysisEngine,
        private readonly AnalysisResultDAO $analysisResultDAO,
        private readonly UserDAO $userDAO,
    ) {
    }

    /**
     * @param int $userId
     * @return array<DigitalItem>
     */
    public function getByUserId(int $userId): array
    {
        return $this->digitalItemDAO->getByUserId($userId);
    }

    public function getById(int $itemId): ?DigitalItem
    {
        return $this->digitalItemDAO->getById($itemId);
    }

    /**
     * @param int $itemId
     * @return array<int> list of user ids that are allowed to access the item
     */
    public function getOwnerIds(int $itemId): array
    {
        return $this->digitalItemDAO->getOwnerIds($itemId);
    }

    public function getContent(int $itemId): ?string
    {
        return $this->digitalItemDAO->getContent($itemId);
    }

    public function analyze(int $maxAmount = 1): void
    {
        for ($i = 0; $i < $maxAmount; $i++) {
            $item = $this->digitalItemDAO->getRegisteredAndMarkAsProcessing();
            if ($item === null) {
                return;
            }

            if ($item->id === null) {
                throw new AssertionError("Item has to have an ID");
            }

            $this->logger?->info("Analyzing digital item: $item->name ($item->id)");

            try {
                $user = null;
                $ownerIds = $this->digitalItemDAO->getOwnerIds($item->id);
                if ($ownerIds !== []) {
                    $userId = array_values($ownerIds)[0];
                    $user = $this->userDAO->getById($userId);
                }

                $content = $this->digitalItemDAO->getContent($item->id);
                if ($content !== null) {
                    $results = $this->analysisEngine->analyze($user, $item, $content);
                    foreach ($results as $result) {
                        $this->analysisResultDAO->insert($item->id, $result);
                    }
                }
            } finally {
                $this->digitalItemDAO->markAsProcessed($item->id);
                $this->logger?->info("Done: $item->name");
            }
        }
    }

    /**
     * @param int $itemId
     * @return array<AnalysisResult>
     */
    public function getAnalysisResults(int $itemId): array
    {
        return $this->analysisResultDAO->getByItemId($itemId);
    }

    public function removeItemsOlderThan(\DateTimeInterface $limit): int
    {
        return $this->digitalItemDAO->removeOlderThan($limit);
    }
}
