<?php

namespace App\Controllers;

use App\Model\Route;
use App\Routes;
use App\Service\RankingService;

class RankingController
{
    public function __construct(
        private readonly \App\UI\Template $template,
        private readonly RankingService $rankingService
    ) {
    }

    #[Route(Routes::RANKING)]
    public function ranking(): string
    {
        $ranking = $this->rankingService->getCurrentRanking();
        $rankingTemplate = $this->template->dynamicTemplate("ranking.php", ranking: $ranking);
        return $this->template->withMainLayout("Ranking", $rankingTemplate);
    }
}
