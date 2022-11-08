<?php

namespace App\Service;

use App\Model\PhysicalItem;
use App\Persistence\PhysicalItemDAO;

class PhysicalItemService
{
    public function __construct(private readonly PhysicalItemDAO $physicalItemDAO)
    {
    }

    /**
     * @param int $userId
     * @return array<PhysicalItem>
     */
    public function getByUserId(int $userId): array
    {
        return $this->physicalItemDAO->getByUserId($userId);
    }

    public function getById(int $itemId): ?PhysicalItem
    {
        return $this->physicalItemDAO->getById($itemId);
    }

    /**
     * @param int $itemId
     * @return array<int> list of user ids that are allowed to access the item
     */
    public function getOwnerIds(int $itemId): array
    {
        return $this->physicalItemDAO->getOwnerIds($itemId);
    }

    public function removeItemsOlderThan(\DateTimeInterface $limit): int
    {
        return $this->physicalItemDAO->removeOlderThan($limit);
    }
}
