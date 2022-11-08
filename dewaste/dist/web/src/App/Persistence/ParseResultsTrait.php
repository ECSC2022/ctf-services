<?php

namespace App\Persistence;

/**
 * @template T
 */
trait ParseResultsTrait
{
    /**
     * @param \PDOStatement $stmt
     * @return array<T>
     */
    private function parseResults(\PDOStatement $stmt): array
    {
        $ret = [];
        while ($row = $stmt->fetch(\PDO::FETCH_ASSOC)) {
            $ret[] = $this->parseRow($row);
        }
        return $ret;
    }

    /**
     * @param array<string,string> $row
     * @return T
     */
    abstract protected function parseRow(array $row): object;
}
