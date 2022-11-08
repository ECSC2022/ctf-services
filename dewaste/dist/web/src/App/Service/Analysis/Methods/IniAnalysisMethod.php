<?php

namespace App\Service\Analysis\Methods;

use App\Model\Analysis\IniAnalysisResult;
use App\Model\DigitalItem;
use App\Model\User;
use App\Service\Analysis\AnalysisMethod;

class IniAnalysisMethod extends AnalysisMethod
{
    public function __construct()
    {
        parent::__construct("ini-extractor");
    }

    public function run(?User $user, DigitalItem $item, string $data): array
    {
        $ret = preg_match_all("/(?:(?:(?:\[\w+])|(?:[a-zA-Z0-9]+\s*=\s*[^=\n\x7f-\xff]*))\r?\n)+/", $data, $matches);
        if ($ret === false) {
            return [];
        }

        $ret = [];
        $iniStrings = $matches[0];
        foreach ($iniStrings as $iniString) {
            $iniData = @parse_ini_string($iniString, true);
            if ($iniData === false || $iniData === []) {
                continue;
            }
            $ret[] = new IniAnalysisResult($iniData);
        }
        return $ret;
    }
}
