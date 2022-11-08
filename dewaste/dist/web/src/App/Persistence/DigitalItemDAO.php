<?php

namespace App\Persistence;

use App\Model\DigitalItem;
use App\Model\DigitalItemStatus;
use App\Persistence\QueryBuilder\Clause;
use AssertionError;

class DigitalItemDAO
{
    /** @use ParseResultsTrait<DigitalItem> */
    use ParseResultsTrait;

    private const TABLE = "digital_items";

    public function __construct(
        private readonly PDO $db
    ) {
    }

    public function insert(DigitalItem $item, string $content): void
    {
        $stmt = $this->db->prepare(<<<SQL
INSERT INTO digital_items 
    (name, description, size, authtoken, status, content)
VALUES
    (?,?,?,?,?,?)
SQL
        );
        $stmt->execute(
            [
                $item->name,
                $item->description,
                $item->size,
                $item->authToken,
                $item->status->value,
                base64_encode($content)
            ]
        );
        $item->id = (int) $this->db->lastInsertId();
    }

    public function linkToUser(int $itemId, int $userId): void
    {
        $this->db->getQueryBuilder()
            ->insert("digital_item_ownerships", ["digitalItemId", "userId"])
            ->data($itemId, $userId)
            ->execute();
    }

    public function getById(int $itemId): ?DigitalItem
    {
        $stmt = $this->db->getQueryBuilder()
            ->select(self::TABLE)
            ->where(Clause::equal("id", $itemId))
            ->limit(1)
            ->query();

        if ($stmt->rowCount() === 0) {
            return null;
        }

        return $this->parseResults($stmt)[0];
    }

    /**
     * @param int $userId
     * @return array<DigitalItem>
     */
    public function getByUserId(int $userId): array
    {
        $stmt = $this->db->getQueryBuilder()
            ->select(self::TABLE, "i")
            ->join("digital_item_ownerships", "o", "i.id", "o.digitalItemId")
            ->where(Clause::equal("userId", $userId))
            ->query();

        return $this->parseResults($stmt);
    }

    /**
     * @param int $itemId
     * @return array<int>
     */
    public function getOwnerIds(int $itemId): array
    {
        $stmt = $this->db->getQueryBuilder()
            ->select("digital_item_ownerships")
            ->where(Clause::equal("digitalItemId", $itemId))
            ->query();
        return array_map(fn(array $row) => (int)$row["userid"], $stmt->fetchAll(\PDO::FETCH_ASSOC));
    }

    public function getContent(int $itemId): ?string
    {
        $stmt = $this->db->prepare(<<<SQL
SELECT content FROM digital_items WHERE id = ?
SQL
        );
        $stmt->execute([$itemId]);
        $row = $stmt->fetch(\PDO::FETCH_ASSOC);
        if ($row === false) {
            return null;
        }
        if (!is_array($row) || !isset($row["content"])) {
            throw new AssertionError("Database response does not include 'content'");
        }
        return base64_decode(fgets($row["content"]) ?: "");
    }

    public function getRegisteredAndMarkAsProcessing(): ?DigitalItem
    {
        $stmt = $this->db->query(<<<SQL
UPDATE digital_items 
    SET status='processing' 
WHERE id = (SELECT id FROM digital_items WHERE status='uploaded' ORDER BY id LIMIT 1) 
RETURNING id, name, description, size, authtoken, status, createdat
SQL
        );
        if ($stmt === false) {
            throw new AssertionError("PDO is in the wrong error mode (EXCEPTION expected)");
        }
        if ($stmt->rowCount() === 0) {
            return null;
        }

        $row = $stmt->fetch(\PDO::FETCH_ASSOC);
        return $this->parseRow($row);
    }

    /**
     * @param array{id:int,name:string,description:string,size:int,authtoken:string,status:string,createdat:string} $row
     * @return DigitalItem
     */
    protected function parseRow(array $row): DigitalItem
    {
        return new DigitalItem(
            $row["id"],
            $row["name"],
            $row["description"],
            $row["size"],
            $row["authtoken"],
            DigitalItemStatus::from($row["status"]),
            \DateTime::createFromFormat("Y-m-d H:i:s", substr($row["createdat"], 0, 19)) ?: null
        );
    }

    public function markAsProcessed(int $id): void
    {
        $stmt = $this->db->prepare(<<<SQL
UPDATE digital_items 
SET status = 'processed' 
WHERE id = ?
SQL);
        $stmt->execute([$id]);
    }

    public function removeOlderThan(\DateTimeInterface $limit): int
    {
        $stmt = $this->db->prepare(<<<SQL
DELETE FROM digital_items WHERE createdat < ?
SQL);
        $stmt->execute([$limit->format("Y-m-d H:i:s")]);
        return $stmt->rowCount();
    }
}
