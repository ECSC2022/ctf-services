<?php

namespace App\Persistence\QueryBuilder;

class AlnumGenerator
{
    private const CHARSET = "0123456789abcdefghijklmnopqrstuvwxyz";

    public function generate(): string
    {
        return $this->generateRec("a", (mt_rand() % 20) + 1);
    }

    private function generateRec(string $x, int $level): string
    {
        if ($level === 0) {
            return $x;
        }
        $x .= substr(self::CHARSET, mt_rand() % strlen(self::CHARSET), 1);
        return $this->generateRec($x, $level - 1);
    }
}
