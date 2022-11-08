<?php

namespace App\Model;

use RuntimeException;

class Redirection extends RuntimeException
{
    public function __construct(private string $target)
    {
    }

    public function getTarget(): string
    {
        return $this->target;
    }
}
