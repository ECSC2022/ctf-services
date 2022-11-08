<?php

namespace App\Service;

use App\Model\User;
use App\Persistence\StatsDAO;
use App\Persistence\UserDAO;

class RankingService
{
    public function __construct(private readonly UserDAO $userDAO, private readonly StatsDAO $statsDAO)
    {
    }

    /**
     * @return array<array{user:User, num_physical: int, num_digital: int, bytes_digital: int}>
     */
    public function getCurrentRanking(): array
    {
        $users = $this->userDAO->getAll();
        $stats = $this->statsDAO->getStatsForAll();

        $ret = [];
        foreach ($stats as $stat) {
            $user = $users[$stat["userid"]] ?? null;
            if ($user === null) {
                continue;
            }
            $ret[] = [
                "user" => $user,
                "num_physical" => $stat["num_physical"],
                "num_digital" => $stat["num_digital"],
                "bytes_digital" => $stat["bytes_digital"],
            ];
        }
        return $ret;
    }
}
