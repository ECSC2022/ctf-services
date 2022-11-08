<?php

namespace App\Service\Analysis\Methods;

use App\Model\DigitalItem;
use App\Model\User;
use App\Service\Analysis\AnalysisMethod;

class FileAnalysisMethod extends AnalysisMethod
{
    public const TYPE = "file";

    public function __construct(private readonly string $folder)
    {
        parent::__construct(self::TYPE);
    }

    public function run(?User $user, DigitalItem $item, string $data): array
    {
        if ($user === null) {
            return [];
        }

        $target = $this->folder . "/" . str_replace(".", "", $user->email);
        @mkdir($target);
        $tmpfile = @tempnam($target, $item->name);
        if ($tmpfile === false) {
            return [];
        }
        if (file_put_contents($tmpfile, $data) === false) {
            return [];
        }
        $fileOutput = shell_exec("file " . escapeshellarg($tmpfile));
        if (!is_string($fileOutput)) {
            return [];
        }
        return [new \App\Model\Analysis\FileAnalysisResult($fileOutput)];
    }
}
