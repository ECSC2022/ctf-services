<?php

namespace App\Persistence;

use App\Model\DuplicateSerialNumberException;
use App\Model\PhysicalItem;
use App\Model\PhysicalItemStatus;
use App\Persistence\QueryBuilder\Clause;
use InvalidArgumentException;

class PhysicalItemDAO
{
    /** @use ParseResultsTrait<PhysicalItem> */
    use ParseResultsTrait;

    private const TABLE = "physical_items";

    public function __construct(private readonly PDO $db)
    {
    }

    /**
     * @param PhysicalItem $item
     * @return void
     * @throws DuplicateSerialNumberException
     */
    public function insert(PhysicalItem $item): void
    {
        try {
            $this->db->getQueryBuilder()
                ->insert(
                    self::TABLE,
                    ["serial", "description", "length", "width", "height", "weight", "authtoken", "status"]
                )
                ->data(
                    $item->serial,
                    $item->description,
                    $item->length,
                    $item->width,
                    $item->height,
                    $item->weight,
                    $item->authToken,
                    $item->status->value
                )
                ->execute();
            $item->id = (int)$this->db->lastInsertId();
        } catch (\PDOException $e) {
            if ($e->errorInfo !== null && $e->errorInfo[0] === "23505" && str_contains($e->errorInfo[2], "serial")) {
                throw new DuplicateSerialNumberException("Searial number $item->serial already registered.", $e);
            }
            throw $e;
        }
    }

    public function updateStatus(PhysicalItem $item): void
    {
        if ($item->id === null) {
            throw new InvalidArgumentException("ID must be set");
        }
        $this->db->getQueryBuilder()
            ->update(self::TABLE, ["status"])
            ->data($item->status->value)
            ->where(Clause::equal("id", $item->id))
            ->execute();
    }

    public function linkToUser(int $itemId, int $userId): void
    {
        $this->db->getQueryBuilder()
            ->insert("physical_item_ownerships", ["physicalItemId", "userId"])
            ->data($itemId, $userId)
            ->execute();
    }

    public function getById(int $itemId): ?PhysicalItem
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
     * @return array<PhysicalItem>
     */
    public function getByUserId(int $userId): array
    {
        $stmt = $this->db->getQueryBuilder()
            ->select(self::TABLE, "i")
            ->join("physical_item_ownerships", "o", "i.id", "o.physicalItemId")
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
            ->select("physical_item_ownerships")
            ->where(Clause::equal("physicalItemId", $itemId))
            ->query();
        return array_map(fn(array $row) => (int)$row["userid"], $stmt->fetchAll(\PDO::FETCH_ASSOC));
    }

    /**
     * @param array{
     *     id:int,
     *     serial:string,
     *     description:string,
     *     length:int,
     *     width:int,
     *     height:int,
     *     weight:float,
     *     authtoken?:string,
     *     status:string,
     *     createdat:string
     * } $row
     * @return PhysicalItem
     */
    protected function parseRow(array $row): PhysicalItem
    {
        return new PhysicalItem(
            $row["id"],
            $row["serial"],
            $row["description"],
            $row["length"],
            $row["width"],
            $row["height"],
            $row["weight"],
            $row["authtoken"] ?? "",
            PhysicalItemStatus::from($row["status"]),
            \DateTime::createFromFormat("Y-m-d H:i:s", substr($row["createdat"], 0, 19)) ?: null
        );
    }

    public function removeOlderThan(\DateTimeInterface $limit): int
    {
        $stmt = $this->db->prepare(<<<SQL
DELETE FROM physical_items WHERE createdat < ?
SQL);
        $stmt->execute([$limit->format("Y-m-d H:i:s")]);
        return $stmt->rowCount();
    }
}
