<?php

namespace App\Persistence\QueryBuilder;

use InvalidArgumentException;
use PDOStatement;

class UpdateStatement
{
    private ?int $limit = null;
    private ?AbstractClause $where = null;
    /** @var array<int|string|float>|null  */
    private ?array $data = null;

    /**
     * @param \PDO $db
     * @param string $table
     * @param array<string> $fields
     */
    public function __construct(
        private readonly \PDO $db,
        private readonly string $table,
        private readonly array $fields = []
    ) {
    }

    /**
     * @return PDOStatement
     * @throws InvalidArgumentException in case no data is set
     */
    public function execute(): PDOStatement
    {
        if ($this->data === null) {
            throw new InvalidArgumentException("No data set");
        }

        $sql = $this->buildQuery();
        try {
            $stmt = $this->db->prepare($sql);
            $stmt->execute($this->data);
            return $stmt;
        } catch (\PDOException $e) {
            error_log("SQL Error: $sql");
            throw new \RuntimeException("Could not perform query", 0, $e);
        }
    }

    public function where(?AbstractClause $where): self
    {
        $this->where = $where;
        return $this;
    }

    public function limit(?int $limit): self
    {
        $this->limit = $limit;
        return $this;
    }

    public function data(string ...$data): self
    {
        if (count($this->fields) !== count($data)) {
            throw new InvalidArgumentException("Invalid column count");
        }
        $this->data = $data;
        return $this;
    }

    private function buildQuery(): string
    {
        $updateFields = implode(
            ",",
            array_map(fn(string $x) => "\"" . strtolower($x) . "\" = ?", $this->fields)
        );
        $whereStr = "";
        if ($this->where !== null) {
            $whereStr = "WHERE " . $this->where->render();
        }
        $limitStr = "";
        if ($this->limit !== null) {
            $limitStr = "LIMIT $this->limit";
        }
        return "update \"$this->table\" SET $updateFields $whereStr $limitStr";
    }
}
