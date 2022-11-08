<?php

namespace App\Model;

enum DigitalItemStatus: string
{
    case UPLOADED = 'uploaded';
    case PROCESSING = 'processing';
    case PROCESSED = 'processed';
}
