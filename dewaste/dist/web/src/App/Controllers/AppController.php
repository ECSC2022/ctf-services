<?php

namespace App\Controllers;

use App\Model\Route;
use App\Routes;
use App\UI\Template;

class AppController
{
    public function __construct(private readonly Template $template)
    {
    }

    #[Route(Routes::INDEX)]
    public function index(): string
    {
        $homePage = $this->template->dynamicTemplate("home.php");
        return $this->template->withMainLayout("Home", $homePage);
    }

    #[Route(Routes::ANALYZE)]
    public function analyze(): string
    {
        $analyzePage = $this->template->staticFile("analyze.html");
        return $this->template->withMainLayout("Analyze", $analyzePage);
    }

    #[Route(Routes::ABOUT)]
    public function about(): string
    {
        $aboutPage = $this->template->staticFile("about.html");
        return $this->template->withMainLayout("About", $aboutPage);
    }
}
