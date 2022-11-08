<?php

use App\Routes;

/** @var string|null $active */
$active ??= "";
?>
    <h2>Recycle</h2>
    <p>
        <?= PLANT_NAME ?> can recycle electronic junk and old archives. If you are interested in our
        physical and digital processing methodology, please visit the
        <a href="<?= Routes::FAQ ?>">FAQ</a> page.
    </div>

    <div class="recycle-nav">
        <a href="<?= Routes::RECYCLE_PHYSICAL_REGISTER ?>"
           class="button <?= $active === "physical" ? "disabled" : "" ?>">
           E-waste
        </a>
        <a href="<?= Routes::RECYCLE_DIGITAL_REGISTER ?>"
           class="button <?= $active === "digital" ? "disabled" : "" ?>">
           Digital Archives
        </a>
    </div>

<?= $content ?? "" ?>