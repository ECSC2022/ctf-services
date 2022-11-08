<?php

namespace App\Persistence;

class DatabaseManager
{
    public function __construct(
        private string $host,
        private string $user,
        private string $password,
        private string $name
    ) {
    }

    public function getNewConnection(): PDO
    {
        $db = new PDO("pgsql:host=$this->host;port=5432;dbname=$this->name;", $this->user, $this->password);
        $db->setAttribute(\PDO::ATTR_ERRMODE, \PDO::ERRMODE_EXCEPTION);
        $db->setAttribute(\PDO::ATTR_EMULATE_PREPARES, true);
        return $db;
    }
}
