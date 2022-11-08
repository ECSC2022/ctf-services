<?php

use App\Model\PhysicalItem;

/** @var PhysicalItem|null $item */
$item ??= null;
?>

<h2>Item</h2>

<dt>Type:</dt>
<dd>Physical</dd>

<dt>S/N:</dt>
<dd class="serial"><?= htmlspecialchars($item?->serial ?? "") ?></dd>

<dt>Dimensions:</dt>
<dd><?="$item?->length/$item?->width/$item?->height"?> cm</dd>

<dt>Weight:</dt>
<dd><?=$item?->weight?> kg</dd>

<dt>Status:</dt>
<dd class="status status-<?=$item?->status->value?>"><?=ucfirst($item?->status->value ?? "")?></dd>

<dt>Description:</dt>
<dd><pre><?=htmlspecialchars($item?->description ?? "")?></pre></dd>
