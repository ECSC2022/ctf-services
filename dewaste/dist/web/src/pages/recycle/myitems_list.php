<?php

use App\Model\DigitalItem;
use App\Model\PhysicalItem;
use App\Routes;

/** @var array<PhysicalItem>|null $physicalItems */
$physicalItems ??= [];
/** @var array<DigitalItem>|null $digitalItems */
$digitalItems ??= [];
?>

<div>
    <h2>Physical items</h2>
    <table class="table table-dark">
        <thead>
        <tr>
            <th>Serial number</th>
            <th>Registered at</th>
            <th>Status</th>
            <th></th>
        </tr>
        </thead>
        <tbody>
        <?php
        foreach ($physicalItems as $item) {
                $item->id ?? throw new AssertionError("ID must be set");
            ?>
            <tr>
                <td><?= htmlspecialchars($item->serial) ?></td>
                <td><?= $item->createdAt?->format("Y-m-d") ?></td>
                <td><?= htmlspecialchars($item->status->value) ?></td>
                <td><a href="<?= Routes::recycleMyItemsPhysical($item->id) ?>">View</a></td>
            </tr>
            <?php
        }
        if ($physicalItems === []) {
            ?>
            <tr>
                <td class="text-center" colspan="99">
                    No items yet.
                </td>
            </tr>
            <?php
        }
        ?>
        </tbody>
    </table>
    <a class="button" role="button" href="<?= Routes::RECYCLE_PHYSICAL_REGISTER ?>">New registration</a>
</div>
<br>
<div>
    <h2>Digital items</h2>
    <table class="table table-dark">
        <thead>
        <tr>
            <th>Registered at</th>
            <th>Size</th>
            <th>Status</th>
            <th></th>
        </tr>
        </thead>
        <tbody>
        <?php
        foreach ($digitalItems as $item) {
                $item->id ?? throw new AssertionError("ID must be set");
            ?>
            <tr>
                <td><?= $item->createdAt?->format("Y-m-d") ?></td>
                <td><?= $item->size / 1000 > 1 ? number_format($item->size / 1000) : "<1" ?>KB</td>
                <td><?= htmlspecialchars($item->status->value) ?></td>
                <td><a href="<?= Routes::recycleMyItemsDigital($item->id) ?>">View</a></td>
            </tr>
            <?php
        }
        if ($digitalItems === []) {
            ?>
            <tr>
                <td class="text-center" colspan="99">
                    No items yet.
                </td>
            </tr>
            <?php
        }
        ?>
        </tbody>
    </table>
    <a class="button" role="button" href="<?= Routes::RECYCLE_DIGITAL_REGISTER ?>">New upload</a>
</div>