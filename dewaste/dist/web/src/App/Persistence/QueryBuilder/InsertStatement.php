<?php

namespace App\Persistence\QueryBuilder;

class InsertStatement
{
    /**
     * @param \PDO $db
     * @param string $table
     * @param array<string> $fields
     * @param array<array<int|string|float>> $data
     */
    public function __construct(
        private readonly \PDO $db,
        private readonly string $table,
        private readonly array $fields,
        private array $data = []
    ) {
    }

    public function data(string|int|float ...$data): self
    {
        if (count($this->fields) !== count($data)) {
            throw new \InvalidArgumentException("Invalid column count");
        }
        $this->data[] = $data;
        return $this;
    }

    /**
     * @param array<array<string|int|float>> $dataList
     * @return $this
     */
    public function dataList(array $dataList): self
    {
        foreach ($dataList as $entry) {
            $this->data(...$entry);
        }
        return $this;
    }

    private function renderValues(): string
    {
        $ret = "";
        foreach ($this->data as $row) {
            $ret .= "(" . implode(",", array_map(fn($x) => new Value($x), $row)) . ")";
        }
        return $ret;
    }

    private function buildQuery(): string
    {
        $renderedValues = $this->renderValues();

        $fieldsStr = implode(
            ",",
            array_map(fn($x) => "\"" . strtolower($x) . "\"", $this->fields)
        );
        return "insert into \"$this->table\" ($fieldsStr) VALUES $renderedValues";
    }

    public function execute(): \PDOStatement
    {
        $sql = $this->buildQuery();
        return $this->db->query($sql) ?: throw new \AssertionError("PDO error mode should be EXCEPTION.");
    }
}
