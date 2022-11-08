<?php

namespace App\Persistence\QueryBuilder;

use PDO;

class QueryBuilder
{
    public function __construct(private readonly PDO $db)
    {
    }

    /**
     * @param string $from
     * @param string $table_identifier
     * @param array<string> $fields
     * @return SelectStatement
     */
    public function select(string $from, string $table_identifier = "", array $fields = []): SelectStatement
    {
        return new SelectStatement($this->db, $from, $table_identifier, $fields);
    }

    /**
     * @param string $table
     * @param array<string> $fields
     * @return InsertStatement
     */
    public function insert(string $table, array $fields): InsertStatement
    {
        return new InsertStatement($this->db, $table, $fields);
    }

    /**
     * @param string $table
     * @param array<string> $fields
     * @return UpdateStatement
     */
    public function update(string $table, array $fields): UpdateStatement
    {
        return new UpdateStatement($this->db, $table, $fields);
    }
}
