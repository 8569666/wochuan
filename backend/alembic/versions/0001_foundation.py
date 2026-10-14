"""Foundation schema snapshot; MySQL 8.0, no runtime model imports."""
from alembic import op

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.execute('\nCREATE TABLE werp_auth_limits (\n\t`key` VARCHAR(64) NOT NULL, \n\tfailures INTEGER NOT NULL, \n\twindow_start DATETIME(6) NOT NULL, \n\tPRIMARY KEY (`key`)\n)ENGINE=InnoDB CHARSET=utf8mb4\n\n')
    op.execute('\nCREATE TABLE werp_colors (\n\thex_value VARCHAR(7), \n\tcode VARCHAR(64) NOT NULL, \n\tname VARCHAR(128) NOT NULL, \n\tstatus VARCHAR(16) NOT NULL, \n\tid BIGINT NOT NULL AUTO_INCREMENT, \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (code)\n)ENGINE=InnoDB CHARSET=utf8mb4\n\n')
    op.execute('\nCREATE TABLE werp_size_groups (\n\tcode VARCHAR(64) NOT NULL, \n\tname VARCHAR(128) NOT NULL, \n\tstatus VARCHAR(16) NOT NULL, \n\tid BIGINT NOT NULL AUTO_INCREMENT, \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (code)\n)ENGINE=InnoDB CHARSET=utf8mb4\n\n')
    op.execute('\nCREATE TABLE werp_stores (\n\ttype VARCHAR(16) NOT NULL, \n\tregion VARCHAR(64), \n\taddress VARCHAR(255), \n\tcontact_phone VARCHAR(32), \n\tcode VARCHAR(64) NOT NULL, \n\tname VARCHAR(128) NOT NULL, \n\tstatus VARCHAR(16) NOT NULL, \n\tid BIGINT NOT NULL AUTO_INCREMENT, \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (code)\n)ENGINE=InnoDB CHARSET=utf8mb4\n\n')
    op.execute('\nCREATE TABLE werp_suppliers (\n\tcontact_name VARCHAR(64), \n\tcontact_phone VARCHAR(32), \n\taddress VARCHAR(255), \n\tsettlement VARCHAR(32) NOT NULL, \n\tnotes TEXT, \n\tcode VARCHAR(64) NOT NULL, \n\tname VARCHAR(128) NOT NULL, \n\tstatus VARCHAR(16) NOT NULL, \n\tid BIGINT NOT NULL AUTO_INCREMENT, \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (code)\n)ENGINE=InnoDB CHARSET=utf8mb4\n\n')
    op.execute('\nCREATE TABLE werp_users (\n\tusername VARCHAR(64) NOT NULL, \n\tdisplay_name VARCHAR(128) NOT NULL, \n\tpassword_hash VARCHAR(256) NOT NULL, \n\t`role` VARCHAR(32) NOT NULL, \n\tstatus VARCHAR(16) NOT NULL, \n\tid BIGINT NOT NULL AUTO_INCREMENT, \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (username)\n)ENGINE=InnoDB CHARSET=utf8mb4\n\n')
    op.execute('\nCREATE TABLE werp_audit_logs (\n\tactor_id BIGINT NOT NULL, \n\taction VARCHAR(32) NOT NULL, \n\tentity_type VARCHAR(64) NOT NULL, \n\tentity_id BIGINT NOT NULL, \n\tchanges JSON NOT NULL, \n\tid BIGINT NOT NULL AUTO_INCREMENT, \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(actor_id) REFERENCES werp_users (id)\n)ENGINE=InnoDB CHARSET=utf8mb4\n\n')
    op.execute('\nCREATE TABLE werp_products (\n\tcategory VARCHAR(64) NOT NULL, \n\tyear INTEGER NOT NULL, \n\tseason VARCHAR(16) NOT NULL, \n\twave_band VARCHAR(32), \n\tfabric_composition TEXT, \n\tsafety_category VARCHAR(32) NOT NULL, \n\ttag_price NUMERIC(12, 2) NOT NULL, \n\tpurchase_base_price NUMERIC(12, 2), \n\tmin_retail_price NUMERIC(12, 2), \n\tsize_group_id BIGINT NOT NULL, \n\tcode VARCHAR(64) NOT NULL, \n\tname VARCHAR(128) NOT NULL, \n\tstatus VARCHAR(16) NOT NULL, \n\tid BIGINT NOT NULL AUTO_INCREMENT, \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(size_group_id) REFERENCES werp_size_groups (id), \n\tUNIQUE (code)\n)ENGINE=InnoDB CHARSET=utf8mb4\n\n')
    op.execute('\nCREATE TABLE werp_sessions (\n\tuser_id BIGINT NOT NULL, \n\ttoken_hash VARCHAR(64) NOT NULL, \n\texpires_at DATETIME(6) NOT NULL, \n\tid BIGINT NOT NULL AUTO_INCREMENT, \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(user_id) REFERENCES werp_users (id), \n\tUNIQUE (token_hash)\n)ENGINE=InnoDB CHARSET=utf8mb4\n\n')
    op.execute('\nCREATE TABLE werp_sizes (\n\tcode VARCHAR(16) NOT NULL, \n\tgroup_id BIGINT NOT NULL, \n\tposition INTEGER NOT NULL, \n\tname VARCHAR(128) NOT NULL, \n\tstatus VARCHAR(16) NOT NULL, \n\tid BIGINT NOT NULL AUTO_INCREMENT, \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (group_id, code), \n\tFOREIGN KEY(group_id) REFERENCES werp_size_groups (id)\n)ENGINE=InnoDB CHARSET=utf8mb4\n\n')
    op.execute('\nCREATE TABLE werp_warehouses (\n\ttype VARCHAR(16) NOT NULL, \n\tstore_id BIGINT, \n\tcode VARCHAR(64) NOT NULL, \n\tname VARCHAR(128) NOT NULL, \n\tstatus VARCHAR(16) NOT NULL, \n\tid BIGINT NOT NULL AUTO_INCREMENT, \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (store_id), \n\tFOREIGN KEY(store_id) REFERENCES werp_stores (id), \n\tUNIQUE (code)\n)ENGINE=InnoDB CHARSET=utf8mb4\n\n')
    op.execute('\nCREATE TABLE werp_skus (\n\tproduct_id BIGINT NOT NULL, \n\tcolor_id BIGINT NOT NULL, \n\tsize_id BIGINT NOT NULL, \n\tcode VARCHAR(64) NOT NULL, \n\tbarcode VARCHAR(64) NOT NULL, \n\tretail_price NUMERIC(12, 2) NOT NULL, \n\tid BIGINT NOT NULL AUTO_INCREMENT, \n\tcreated_at DATETIME(6) NOT NULL, \n\tupdated_at DATETIME(6) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (product_id, color_id, size_id), \n\tFOREIGN KEY(product_id) REFERENCES werp_products (id), \n\tFOREIGN KEY(color_id) REFERENCES werp_colors (id), \n\tFOREIGN KEY(size_id) REFERENCES werp_sizes (id), \n\tUNIQUE (code), \n\tUNIQUE (barcode)\n)ENGINE=InnoDB CHARSET=utf8mb4\n\n')
    op.execute('CREATE INDEX ix_werp_sessions_expires_at ON werp_sessions (expires_at)')

def downgrade():
    op.drop_table('werp_skus')
    op.drop_table('werp_warehouses')
    op.drop_table('werp_sizes')
    op.drop_table('werp_sessions')
    op.drop_table('werp_products')
    op.drop_table('werp_audit_logs')
    op.drop_table('werp_users')
    op.drop_table('werp_suppliers')
    op.drop_table('werp_stores')
    op.drop_table('werp_size_groups')
    op.drop_table('werp_colors')
    op.drop_table('werp_auth_limits')
