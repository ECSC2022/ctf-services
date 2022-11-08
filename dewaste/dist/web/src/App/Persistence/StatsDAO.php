<?php

namespace App\Persistence;

class StatsDAO
{
    public function __construct(private readonly PDO $db)
    {
    }

    /**
     * @return array<array{userid:int, num_physical:int, num_digital:int, bytes_digital:int}>
     */
    public function getStatsForAll(): array
    {
        $stmt = $this->db->query(<<<SQL
SELECT 
    u.id as userId,
    sum(CASE WHEN p.id is not null THEN 1 ELSE 0 END) as num_physical, 
    sum(CASE WHEN d.id is not null THEN 1 ELSE 0 END) as num_digital, 
    sum(coalesce(LENGTH(d.content), 0)) as bytes_digital
FROM users u
LEFT JOIN physical_item_ownerships pio on u.id = pio.userid
LEFT JOIN physical_items p on p.id = pio.physicalitemid
LEFT JOIN digital_item_ownerships dio on u.id = dio.userid
LEFT JOIN digital_items d on dio.digitalitemid = d.id
GROUP BY u.id
SQL);
        assert($stmt !== false, "PDO in wrong error mode (EXCEPTION expected)");
        return $stmt->fetchAll(\PDO::FETCH_ASSOC);
    }
}
