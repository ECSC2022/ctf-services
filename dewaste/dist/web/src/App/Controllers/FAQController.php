<?php

namespace App\Controllers;

use App\Model\Route;
use App\Persistence\FAQDAO;
use App\Routes;

class FAQController
{
    public function __construct(
        private readonly \App\UI\Template $template,
        private readonly FAQDAO $faqDAO
    ) {
    }

    #[Route(Routes::FAQ)]
    public function index(): string
    {
        $search = "";
        if (isset($_GET["q"]) && is_string($_GET["q"])) {
            $search = $_GET["q"];
            $tokens = explode(" ", $search);
            $tokens = array_map("trim", $tokens);
            $faqList = $this->faqDAO->searchFulltext($tokens);
        } else {
            $faqList = $this->faqDAO->getAll();
        }
        $content = $this->template->dynamicTemplate("faq.php", search: $search, faqList: $faqList);
        return $this->template->withMainLayout("FAQ", $content);
    }
}
