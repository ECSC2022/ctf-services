<?php

namespace App\Model;

use Exception;
use Throwable;

class DuplicateEmailAddressException extends Exception
{
    public function __construct(string $string, Throwable $e)
    {
        parent::__construct($string, 0, $e);
    }
}
