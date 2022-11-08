<?php

use App\Model\User;

/** @var array<array{user:User, num_physical: int, num_digital: int, bytes_digital: int}>|null $ranking */
$ranking ??= [];

?>

<h2>Current Ranking</h2>

<table class="table table-dark">
    <thead>
    <tr>
        <th>User</th>
        <th>Total physical items</th>
        <th>Total digital items</th>
        <th>Total digital items (bytes)</th>
    </tr>
    </thead>
    <tbody>
    <?php
    $enc = fn(string $x) => htmlspecialchars($x, ENT_QUOTES);
    foreach ($ranking as $rank) {
        $enc_bytes = number_format($rank["bytes_digital"] / 1000, 1);
        echo <<<HTML
<tr data-user-id="{$rank["user"]->id}">
    <td data-contact="{$enc($rank["user"]->email)}">{$enc($rank["user"]->getFullname())}</td>
    <td>$rank[num_physical]</td>
    <td>$rank[num_digital]</td>
    <td>$enc_bytes KB</td>
</tr>
HTML;
    }
    ?>
    </tbody>
</table>
