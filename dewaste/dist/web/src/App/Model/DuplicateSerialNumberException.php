<?php

namespace App\Model;

use Exception;
use Throwable;

class DuplicateSerialNumberException extends Exception
{
    public function __construct(string $message, ?Throwable $cause = null)
    {
        parent::__construct($message, 0, $cause);
    }
}
