<?php

namespace App\Persistence\QueryBuilder;

class SelectStatement
{
    private ?int $limit = null;
    private ?AbstractClause $where = null;
    /**
     * @var array<array{table:string,table_identifier:string,field1:string,field2:string}>
     */
    private array $joins = [];

    /**
     * @param \PDO $db
     * @param string $from
     * @param string $table_identifier
     * @param array<string> $fields
     */
    public function __construct(
        private readonly \PDO $db,
        private readonly string $from,
        private string $table_identifier,
        private readonly array $fields = []
    ) {
        $this->table_identifier = strtolower($table_identifier);
    }

    public function query(): \PDOStatement
    {
        $sql = $this->buildQuery();
        try {
            $stmt = $this->db->prepare($sql);
            $stmt->execute();
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

    private function buildQuery(): string
    {
        $fieldList = implode(",", array_map(fn(string $x) => "\"$x\"", $this->fields));
        if ($fieldList === "") {
            $fieldList = "*";
        }
        $joinStr = "";
        foreach ($this->joins as $join) {
            $joinStr .= "JOIN \"$join[table]\" $join[table_identifier] ON $join[field1] = $join[field2]";
        }
        $joinStr = strtolower($joinStr);

        $whereStr = "";
        if ($this->where !== null) {
            $whereStr = "WHERE " . $this->where->render();
        }
        $limitStr = "";
        if ($this->limit !== null) {
            $limitStr = "LIMIT $this->limit";
        }
        return "select $fieldList from \"$this->from\" $this->table_identifier $joinStr $whereStr $limitStr";
    }

    public function join(string $table, string $name, string $field1, string $field2): self
    {
        $this->joins[] = [
            "table" => $table,
            "table_identifier" => $name,
            "field1" => $field1,
            "field2" => $field2
        ];
        return $this;
    }
}
