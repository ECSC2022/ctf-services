<?php

namespace App\Persistence;

use App\Persistence\QueryBuilder\QueryBuilder;

class PDO extends \PDO
{
    /**
     * @param string $dsn
     * @param string|null $username
     * @param string|null $password
     * @param array<int,int>|null $options
     */
    public function __construct(string $dsn, ?string $username = null, ?string $password = null, ?array $options = null)
    {
        parent::__construct($dsn, $username, $password, $options);
    }

    public function getQueryBuilder(): QueryBuilder
    {
        return new QueryBuilder($this);
    }
}
