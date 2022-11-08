<?php

namespace App\Model;

enum PhysicalItemStatus: string
{
    case REGISTERED = 'registered';
    case HANDEDIN = 'handed in';
    case PROCESSING = 'processing';
    case PROCESSED = 'processed';
}
