<?php

use App\Model\FAQ;

?>
<h2>FAQ</h2>
<div class="faq-search-container">
    <form>
        <input type="text" name="q" placeholder="Search..." value="<?=htmlspecialchars($search ?? "", ENT_QUOTES)?>" />
        <button class="button"><i class="fa fa-search"></i></button>
    </form>
</div>

<div class="faq-list">
    <?php
    /** @var FAQ $faq */
    $faqList = $faqList ?? [];
    foreach ($faqList as $faq) {
        $enc_question = htmlspecialchars($faq->getQuestion());
        $enc_answer = str_replace("%REPORT_APP_URL%", REPORT_APP_URL, $faq->getAnswer());
        echo <<<HTML
    <div class="faq">
        <div class="faq-question">$enc_question</div>
        <div class="faq-answer">$enc_answer</div>
    </div>
HTML;
    }

    if ($faqList === []) {
        echo <<<HTML
    <div class="faq-no-entries">
        No matching FAQ entries found.
    </div>
HTML;
    }
    ?>
</div>
