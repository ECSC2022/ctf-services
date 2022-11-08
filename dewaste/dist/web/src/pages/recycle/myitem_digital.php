<?php

use App\Model\Analysis\AnalysisResult;
use App\Model\DigitalItem;
use App\Routes;

/** @var DigitalItem|null $item */
$item ??= null;
/** @var AnalysisResult[]|null $analysisResults */
$analysisResults ??= [];
?>

    <h2>Item</h2>

    <dt>Type:</dt>
    <dd>Digital</dd>

    <dt>Name:</dt>
    <dd><?= htmlspecialchars($item?->name ?? "") ?></dd>

    <dt>Description:</dt>
    <dd>
        <pre><?= htmlspecialchars($item?->description ?? "") ?></pre>
    </dd>

    <dt>Size:</dt>
    <dd><?= number_format($item?->size / 1000, 2) ?> kB</dd>

    <dt>Status:</dt>
    <dd class="status status-<?= $item?->status->value ?>"><?= ucfirst($item?->status->value ?? "") ?></dd>

<?php
if ($item !== null) {
        $item->id ?? throw new AssertionError("ID must be set");
    ?>
    <a role="button" class="button" href="<?= Routes::digitalItemDownload($item->id, $authToken ?? "") ?>" download>
        Download Data
    </a>
    <?php
}
if ($analysisResults !== []) {
    echo "<h3>Analysis results</h3><div class='analysis-result-list'>";
    foreach ($analysisResults as $result) {
        ?>
        <div class="result">
            <p>Type: <?= $result->type ?></p>
            <pre><?= htmlspecialchars($result->renderData()) ?></pre>
        </div>
        <?php
    }
    echo "</div>";
}