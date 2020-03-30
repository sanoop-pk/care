from django.contrib.auth import get_user_model
from drf_extra_fields.geo_fields import PointField
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from care.facility.api.serializers.facility_capacity import FacilityCapacitySerializer
from care.facility.models import FACILITY_TYPES, Facility, FacilityLocalGovtBody
from care.users.api.serializers.lsg import DistrictSerializer, LocalBodySerializer, StateSerializer
from config.serializers import ChoiceField

User = get_user_model()


class FacilityLocalGovtBodySerializer(serializers.ModelSerializer):
    local_body = LocalBodySerializer()
    district = DistrictSerializer()

    class Meta:
        model = FacilityLocalGovtBody
        fields = "__all__"


class FacilityBasicInfoSerializer(serializers.ModelSerializer):
    local_body_object = LocalBodySerializer(source="local_body", read_only=True)
    district_object = DistrictSerializer(source="district", read_only=True)
    state_object = StateSerializer(source="state", read_only=True)

    class Meta:
        model = Facility
        fields = (
            "id",
            "name",
            "local_body",
            "district",
            "state",
            "local_body_object",
            "district_object",
            "state_object",
        )


class FacilitySerializer(serializers.ModelSerializer):
    """Serializer for facility.models.Facility."""

    facility_type = ChoiceField(choices=FACILITY_TYPES)
    # A valid location => {
    #     "latitude": 49.8782482189424,
    #     "longitude": 24.452545489
    # }
    location = PointField(required=False)

    local_body_object = LocalBodySerializer(source="local_body", read_only=True)
    district_object = DistrictSerializer(source="district", read_only=True)
    state_object = StateSerializer(source="state", read_only=True)

    class Meta:
        model = Facility
        fields = [
            "id",
            "name",
            "local_body",
            "district",
            "state",
            "facility_type",
            "address",
            "location",
            "oxygen_capacity",
            "phone_number",
            "local_body_object",
            "district_object",
            "state_object",
        ]


class FacilityUpsertSerializer(serializers.ModelSerializer):
    """
    Use only for listing and upserting - Upsert based on name and district uniqueness
    """

    capacity = serializers.ListSerializer(child=FacilityCapacitySerializer(), source="facilitycapacity_set")
    location = PointField(required=False)

    class Meta:
        model = Facility
        fields = [
            "id",
            "name",
            "local_body",
            "district",
            "state",
            "facility_type",
            "address",
            "location",
            "oxygen_capacity",
            "phone_number",
            "capacity",
            "created_by",
        ]

    def validate_name(self, value):
        return str(value).strip().replace("  ", " ")

    def validate_phone_number(self, value):
        return str(value).strip().replace("  ", " ")

    def create(self, validated_data):
        capacities = validated_data.pop("facilitycapacity_set")
        facility = Facility.objects.filter(
            **{"name__iexact": validated_data["name"], "district": validated_data["district"],}
        ).first()

        user = self.context["user"]
        if not facility:
            validated_data["created_by"] = user
            facility = Facility.objects.create(**validated_data)
        else:
            if facility.created_by != user and not user.is_superuser:
                raise PermissionDenied(f"{facility} is owned by another user")

            for k, v in validated_data.items():
                setattr(facility, k, v)
            facility.save()

        for ca in capacities:
            facility.facilitycapacity_set.update_or_create(room_type=ca["room_type"], defaults=ca)
        return facility

    def update(self, instance, validated_data):
        raise NotImplementedError()
